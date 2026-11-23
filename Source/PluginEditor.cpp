#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& p)
    : juce::AudioProcessorEditor(&p), processorRef(p)
{
    setSize(420, 220);

    titleLabel.setText("Mono Delay", juce::dontSendNotification);
    titleLabel.setJustificationType(juce::Justification::centred);
    titleLabel.setFont(juce::Font(20.0f, juce::Font::bold));
    addAndMakeVisible(titleLabel);

    // Delay Time Slider
    delayTimeSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    delayTimeSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    delayTimeSlider.setRange(0.0, 3000.0, 1.0);
    delayTimeSlider.setSkewFactorFromMidPoint(500.0); // More resolution at short times
    addAndMakeVisible(delayTimeSlider);

    delayTimeLabel.setText("Delay Time (ms)", juce::dontSendNotification);
    delayTimeLabel.attachToComponent(&delayTimeSlider, true);
    addAndMakeVisible(delayTimeLabel);

    // Mix Slider
    mixSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    mixSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    mixSlider.setRange(0.0, 100.0, 0.1);
    addAndMakeVisible(mixSlider);

    mixLabel.setText("Wet/Dry Mix (%)", juce::dontSendNotification);
    mixLabel.attachToComponent(&mixSlider, true);
    addAndMakeVisible(mixLabel);

    // Attachments
    delayTimeAttachment.reset(new juce::AudioProcessorValueTreeState::SliderAttachment(
        processorRef.parameters, "delayTime", delayTimeSlider));
    mixAttachment.reset(new juce::AudioProcessorValueTreeState::SliderAttachment(
        processorRef.parameters, "mix", mixSlider));
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
    auto sliderHeight = 40;
    delayTimeSlider.setBounds(area.removeFromTop(sliderHeight).reduced(100, 0));
    area.removeFromTop(10);
    mixSlider.setBounds(area.removeFromTop(sliderHeight).reduced(100, 0));
}
