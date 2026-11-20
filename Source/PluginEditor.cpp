#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& p)
    : juce::AudioProcessorEditor(&p), processorRef(p)
{
    title.setText("Mono Delay", juce::dontSendNotification);
    title.setJustificationType(juce::Justification::centred);
    title.setFont(juce::Font(20.0f, juce::Font::bold));
    addAndMakeVisible(title);

    delayTimeLabel.setText("Delay Time (ms)", juce::dontSendNotification);
    delayTimeLabel.attachToComponent(&delayTimeSlider, false);
    addAndMakeVisible(delayTimeLabel);

    delayTimeSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    delayTimeSlider.setRange(1.0, 3000.0, 1.0);
    delayTimeSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 80, 20);
    addAndMakeVisible(delayTimeSlider);

    delayTimeAttachment.reset(new juce::AudioProcessorValueTreeState::SliderAttachment(
        processorRef.parameters, "delayTime", delayTimeSlider));

    setSize(420, 120);
}

void VstAiDemoAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
}

void VstAiDemoAudioProcessorEditor::resized()
{
    auto area = getLocalBounds().reduced(16);
    title.setBounds(area.removeFromTop(32));
    area.removeFromTop(8);
    delayTimeSlider.setBounds(area.removeFromTop(40));
}
