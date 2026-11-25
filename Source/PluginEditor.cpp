#include "PluginEditor.h"

SimpleDelayAudioProcessorEditor::SimpleDelayAudioProcessorEditor(SimpleDelayAudioProcessor& p)
    : juce::AudioProcessorEditor(&p), processor(p)
{
    // Delay Time Slider
    delayTimeSlider.setSliderStyle(juce::Slider::Rotary);
    delayTimeSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 50, 20);
    delayTimeSlider.setRange(1.0, 2000.0);
    delayTimeSlider.setValue(500.0);
    addAndMakeVisible(delayTimeSlider);

    delayTimeLabel.setText("Delay Time (ms)", juce::dontSendNotification);
    delayTimeLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(delayTimeLabel);

    delayTimeAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "delayTime", delayTimeSlider);

    // Mix Slider
    mixSlider.setSliderStyle(juce::Slider::Rotary);
    mixSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 50, 20);
    mixSlider.setRange(0.0, 100.0);
    mixSlider.setValue(50.0);
    addAndMakeVisible(mixSlider);

    mixLabel.setText("Wet/Dry Mix (%)", juce::dontSendNotification);
    mixLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(mixLabel);

    mixAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "mix", mixSlider);

    setSize(400, 300);
}

void SimpleDelayAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
}

void SimpleDelayAudioProcessorEditor::resized()
{
    auto area = getLocalBounds().reduced(20);

    auto topArea = area.removeFromTop(40);
    topArea.removeFromLeft(10);
    delayTimeLabel.setBounds(topArea.removeFromLeft(area.getWidth() / 2 - 20));

    topArea = area.removeFromTop(40);
    topArea.removeFromRight(10);
    mixLabel.setBounds(topArea.removeFromRight(area.getWidth() / 2 - 20));

    auto controlArea = area.reduced(10);
    delayTimeSlider.setBounds(controlArea.removeFromLeft(controlArea.getWidth() / 2).reduced(10));
    mixSlider.setBounds(controlArea.reduced(10));
}
