#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& proc)
    : juce::AudioProcessorEditor(&proc), processor(proc)
{
    titleLabel.setText("Hall Reverb", juce::dontSendNotification);
    titleLabel.setJustificationType(juce::Justification::centred);
    titleLabel.setFont(juce::Font(20.0f, juce::Font::bold));
    addAndMakeVisible(titleLabel);

    decayLabel.setText("Decay", juce::dontSendNotification);
    decayLabel.setJustificationType(juce::Justification::centredLeft);
    addAndMakeVisible(decayLabel);

    decaySlider.setSliderStyle(juce::Slider::LinearHorizontal);
    decaySlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    addAndMakeVisible(decaySlider);

    decayAttachment = std::make_unique<juce::SliderParameterAttachment>(
        *processor.apvts.getParameter("decay"),
        decaySlider);

    setSize(400, 180);
}

void VstAiDemoAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
}

void VstAiDemoAudioProcessorEditor::resized()
{
    auto area = getLocalBounds().reduced(20);

    titleLabel.setBounds(area.removeFromTop(40));
    area.removeFromTop(10);

    auto decayArea = area.removeFromTop(40);
    decayLabel.setBounds(decayArea.removeFromLeft(80));
    decaySlider.setBounds(decayArea);
}
